import { useRef, useState, useEffect, useCallback } from 'react';
import { Data, ChatBoxSettings } from '../types/data';
import { apiFetch } from '@/lib/apiFetch';

const JOB_STORAGE_KEY = 'gptr_active_research_job';
const POLL_INTERVAL_MS = 1500;

type StoredJob = {
  jobId: string;
  sessionId: string;
  tenantId?: string;
};

/** A report started from chat is observed only from its own report page. */
export const researchJobStorageKey = (sessionId?: string) => (
  sessionId ? `${JOB_STORAGE_KEY}:${sessionId}` : JOB_STORAGE_KEY
);

function loadStoredJob(sessionId?: string): StoredJob | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(researchJobStorageKey(sessionId));
    if (!raw) return null;
    return JSON.parse(raw) as StoredJob;
  } catch {
    return null;
  }
}

/** Public helper for report pages that need to know if a Job is in-flight. :-) */
export function loadStoredJobForSession(sessionId?: string): StoredJob | null {
  return loadStoredJob(sessionId);
}

function saveStoredJob(job: StoredJob | null, sessionId?: string) {
  if (typeof window === 'undefined') return;
  const key = researchJobStorageKey(sessionId);
  if (!job) {
    localStorage.removeItem(key);
    return;
  }
  localStorage.setItem(key, JSON.stringify(job));
}

/**
 * Async Job path: POST create → poll GET /api/jobs/{id} every 1.5s.
 * job_id in localStorage enables refresh recovery. Closing the tab does not cancel Worker.
 */
export const useResearchJob = (
  setOrderedData: React.Dispatch<React.SetStateAction<Data[]>>,
  setAnswer: React.Dispatch<React.SetStateAction<string>>,
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setShowHumanFeedback: React.Dispatch<React.SetStateAction<boolean>>,
  setQuestionForHuman: React.Dispatch<React.SetStateAction<boolean | true>>,
  /** Called when a job becomes active (create / resume) so the UI can leave the home hero. :-) */
  onJobActive?: () => void,
  /** When supplied, resume only the Job belonging to this report page. */
  onlySessionId?: string
) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const pollTimer = useRef<number>();
  const lastStage = useRef<string>('');
  const restoredRef = useRef(false);
  const onJobActiveRef = useRef(onJobActive);
  onJobActiveRef.current = onJobActive;

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = undefined;
    }
  }, []);

  /** Stop observing without cancelling the server-side job. :-) */
  const clearActiveJob = useCallback(() => {
    stopPolling();
    saveStoredJob(null, onlySessionId);
    setJobId(null);
    lastStage.current = '';
  }, [onlySessionId, stopPolling]);

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  const applyJobSnapshot = useCallback(
    (job: any, opts?: { appendStageLog?: boolean }) => {
      const status = job?.status as string;
      const stage = (job?.stage || job?.progress || '') as string;
      const result = job?.result || {};
      const report = (result.report || '') as string;

      const progressHint = (job?.progress || stage || '') as string;
      const stageKey = `${status}:${stage}:${progressHint}`;
      const stageLabel: Record<string, string> = {
        planning: '规划中',
        researching: '检索与抓取中',
        writing: '撰写报告中',
        finalizing: '收尾与落库中',
        queued: '排队中',
        running: '执行中',
        pending_dispatch: '等待调度',
      };
      const statusCn = stageLabel[status] || status || '未知';
      const stageCn = stageLabel[stage] || stage;
      const progressCn =
        progressHint && progressHint !== stage ? ` · ${progressHint}` : '';
      const liveLine = `进度：${statusCn}${stageCn ? ` / ${stageCn}` : ''}${progressCn}`;

      // Always upsert a live status line so report-page data reloads cannot
      // leave the UI stuck on a single "queued" placeholder. :-)
      if (
        opts?.appendStageLog &&
        status &&
        !['completed', 'failed', 'cancelled', 'canceled'].includes(status)
      ) {
        setOrderedData((prev) => {
          const withoutLive = prev.filter(
            (item) => (item as { content?: string }).content !== 'job_live_status'
          );
          const next = [
            ...withoutLive,
            {
              type: 'logs',
              content: 'job_live_status',
              output: liveLine,
              contentAndType: 'job_live_status-logs',
            } as Data,
          ];
          if (stageKey && stageKey !== lastStage.current) {
            lastStage.current = stageKey;
            return [
              ...next,
              {
                type: 'logs',
                content: 'job_status',
                output: liveLine,
                contentAndType: 'job_status-logs',
              } as Data,
            ];
          }
          return next;
        });
      } else if (opts?.appendStageLog && stageKey && stageKey !== lastStage.current) {
        lastStage.current = stageKey;
        setOrderedData((prev) => [
          ...prev,
          {
            type: 'logs',
            content: 'job_status',
            output: liveLine,
            contentAndType: 'job_status-logs',
          } as Data,
        ]);
      }

      if (status === 'completed' && report) {
        // Trusted pipeline is out of Project-1 scope — do not surface report_trust labels. :-)
        setAnswer(report);
        setOrderedData((prevOrder) => {
          const withoutReportBlocks = prevOrder.filter((item) => {
            const itemType = (item as { type?: string }).type;
            const content = (item as { content?: string }).content;
            return (
              itemType !== 'report' &&
              itemType !== 'report_complete' &&
              content !== 'report_trust'
            );
          });
          return [
            ...withoutReportBlocks,
            {
              type: 'report_complete',
              output: report,
              content: 'report',
              contentAndType: 'report-report_complete',
            },
          ];
        });
        if (result.file_paths) {
          setOrderedData((prev) => [
            ...prev,
            {
              type: 'path',
              output: result.file_paths,
              content: 'path',
              contentAndType: 'path-path',
            } as Data,
          ]);
        }
        setLoading(false);
        stopPolling();
        saveStoredJob(null, onlySessionId);
        return;
      }

      if (status === 'cancel_requested' || status === 'cancelling') {
        setOrderedData((prev) => {
          const last = prev[prev.length - 1] as { content?: string } | undefined;
          if (last?.content === 'job_cancelling') return prev;
          return [
            ...prev,
            {
              type: 'logs',
              content: 'job_cancelling',
              output: '正在取消研究任务…（停止后续模型/搜索调用）',
              contentAndType: 'job_cancelling-logs',
            } as Data,
          ];
        });
        return;
      }

      if (status === 'failed' || status === 'cancelled') {
        const code = job?.last_error_code ? ` [${job.last_error_code}]` : '';
        const auditFailed =
          job?.last_error_code === 'citation_audit_failed' ||
          result?.citation_audit_failed === true;
        const message = auditFailed
          ? `引用审计未通过，报告未标记为可信完成。${job?.error ? ` ${job.error}` : ''}${code}`
          : `${job?.error || `Job ${status}`}${code}`;
        setOrderedData((prev) => [
          ...prev,
          {
            type: 'logs',
            content: 'error',
            output: message,
            contentAndType: 'error-logs',
          } as Data,
        ]);
        setLoading(false);
        stopPolling();
        saveStoredJob(null, onlySessionId);
      }
    },
    [onlySessionId, setOrderedData, setAnswer, setLoading, stopPolling]
  );

  const pollMisses = useRef(0);

  const pollJob = useCallback(
    async (id: string) => {
      try {
        const resp = await apiFetch(`/api/jobs/${id}`);
        // Fresh jobs can 404 briefly (commit / cookie race). Keep trying. :-)
        if (resp.status === 404) {
          pollMisses.current += 1;
          if (pollMisses.current === 1 || pollMisses.current % 4 === 0) {
            setOrderedData((prev) => {
              const without = prev.filter(
                (item) => (item as { content?: string }).content !== 'job_live_status'
              );
              return [
                ...without,
                {
                  type: 'logs',
                  content: 'job_live_status',
                  output: '正在连接任务进度…（若刚提交请稍候）',
                  contentAndType: 'job_live_status-logs',
                } as Data,
              ];
            });
          }
          if (pollMisses.current >= 40) {
            setOrderedData((prev) => [
              ...prev,
              {
                type: 'logs',
                content: 'error',
                output: '长时间无法读取任务状态（可能已丢失或身份不匹配）。请从左侧重新打开该报告，或重试提交。',
                contentAndType: 'error-logs',
              } as Data,
            ]);
            setLoading(false);
            stopPolling();
          }
          return;
        }
        if (!resp.ok) return;
        pollMisses.current = 0;
        const data = await resp.json();
        const job = data.job || data;
        applyJobSnapshot(job, { appendStageLog: true });
      } catch (err) {
        console.error('Job poll failed:', err);
      }
    },
    [applyJobSnapshot, setOrderedData, setLoading, stopPolling]
  );

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      pollMisses.current = 0;
      lastStage.current = '';
      setJobId(id);
      setLoading(true);
      onJobActiveRef.current?.();
      void pollJob(id);
      pollTimer.current = window.setInterval(() => {
        void pollJob(id);
      }, POLL_INTERVAL_MS);
    },
    [pollJob, stopPolling, setLoading]
  );

  /**
   * Watch an already-created job on the current page (chat → left panel).
   * Persists under the current page session and optionally the report session. :-)
   */
  const observeJob = useCallback(
    (
      id: string,
      opts?: { reportSessionId?: string; tenantId?: string }
    ) => {
      const reportSessionId = opts?.reportSessionId;
      const payload = {
        jobId: id,
        sessionId: reportSessionId || onlySessionId || id,
        tenantId: opts?.tenantId,
      };
      // Current page recovery (chat session stays put).
      saveStoredJob(payload, onlySessionId);
      // Dedicated report entry recovery when opened from the sidebar.
      if (reportSessionId && reportSessionId !== onlySessionId) {
        saveStoredJob(payload, reportSessionId);
      }
      startPolling(id);
    },
    [onlySessionId, startPolling]
  );

  /** Resume in-flight job after page refresh */
  const resumeStoredJob = useCallback(async () => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const stored = loadStoredJob(onlySessionId);
    if (!stored?.jobId) return;
    if (onlySessionId && stored.sessionId !== onlySessionId) return;

    setLoading(true);
    setJobId(stored.jobId);
    onJobActiveRef.current?.();
    setOrderedData((prev) => [
      ...prev,
      {
        type: 'logs',
        content: 'job_resume',
        output: `正在恢复任务进度：${stored.jobId}`,
        contentAndType: 'job_resume-logs',
      } as Data,
    ]);
    startPolling(stored.jobId);
  }, [onlySessionId, setLoading, setOrderedData, startPolling]);

  useEffect(() => {
    void resumeStoredJob();
  }, [resumeStoredJob]);

  const startResearchJob = useCallback(
    async (
      promptValue: string,
      chatBoxSettings: ChatBoxSettings,
      sessionId?: string | null
    ) => {
      setLoading(true);
      setAnswer('');
      // Drop observation of any previous job before creating a new one. :-)
      stopPolling();
      lastStage.current = '';

      const domainFilters = JSON.parse(localStorage.getItem('domainFilters') || '[]');
      const domains = domainFilters
        ? domainFilters.map((domain: { value: string }) => domain.value)
        : [];
      const {
        report_type,
        report_source,
        tone,
        total_words,
        report_language,
        mcp_enabled,
        mcp_configs,
        mcp_strategy,
      } = chatBoxSettings;

      // Backend creates ResearchSession when session_id is omitted.
      // Keep idempotency stable across short retries (same task within the same minute).
      const idempotencyKey = sessionId
        ? `research:${sessionId}`
        : `research:anon:${promptValue.trim().slice(0, 120)}:${Math.floor(Date.now() / 60000)}`;

      const body: Record<string, unknown> = {
        task: promptValue,
        report_type,
        report_source,
        tone,
        total_words: total_words || 1200,
        report_language: report_language || 'chinese',
        query_domains: domains,
        mcp_enabled: mcp_enabled || false,
        mcp_strategy: mcp_strategy || 'fast',
        mcp_configs: mcp_configs || [],
        idempotency_key: idempotencyKey,
      };
      if (sessionId) {
        body.session_id = sessionId;
        body.research_id = sessionId;
      }

      try {
        const resp = await apiFetch('/api/jobs/research', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        // 202 pending_dispatch / 503 with job_id still recoverable via poll
        const detail = data.detail;
        const pendingId =
          data.job_id ||
          (typeof detail === 'object' && detail?.job_id) ||
          null;

        if (resp.status === 429) {
          const retryAfter =
            resp.headers.get('Retry-After') ||
            data.retry_after ||
            (typeof detail === 'object' && detail?.retry_after) ||
            '';
          const msg =
            data.message ||
            (typeof detail === 'object' ? detail?.message : detail) ||
            '系统繁忙或已达限额，请稍后再试';
          const hint = retryAfter
            ? `${msg}（约 ${retryAfter} 秒后可重试）`
            : `${msg}。可取消进行中任务，或稍后再试。`;
          setOrderedData((prev) => [
            ...prev,
            {
              type: 'logs',
              content: 'job_rate_limited',
              output: hint,
              contentAndType: 'job_rate_limited-logs',
            } as Data,
          ]);
          // If a job is already running (per-user concurrency=1), keep watching it
          const activeId =
            pendingId ||
            loadStoredJob(onlySessionId)?.jobId ||
            (typeof detail === 'object' && detail?.active_job_id) ||
            null;
          if (activeId) {
            setOrderedData((prev) => [
              ...prev,
              {
                type: 'logs',
                content: 'job_status',
                output: `已有任务进行中，继续跟踪进度：${activeId}`,
                contentAndType: 'job_status-logs',
              } as Data,
            ]);
            startPolling(String(activeId));
            return;
          }
          setLoading(false);
          return;
        }

        if (!resp.ok && !pendingId) {
          throw new Error(
            typeof detail === 'string'
              ? detail
              : detail?.message || data.error || `Create job failed (${resp.status})`
          );
        }

        const id = (data.job_id || pendingId) as string;
        if (!id) throw new Error('No job_id returned from server');
        const resolvedSession =
          (data.session_id as string) ||
          (typeof detail === 'object' && detail?.session_id) ||
          sessionId ||
          id;

        saveStoredJob({
          jobId: id,
          sessionId: resolvedSession,
          tenantId: data.tenant_id || detail?.tenant_id,
        }, onlySessionId);
        setOrderedData((prev) => [
          ...prev,
          {
            type: 'logs',
            content: 'job_queued',
            output: `任务已创建（${data.status || 'queued'}）：${id}`,
            contentAndType: 'job_queued-logs',
          } as Data,
        ]);
        if (!resp.ok || data.status === 'pending_dispatch') {
          setOrderedData((prev) => [
            ...prev,
            {
              type: 'logs',
              content: 'job_pending_dispatch',
              output:
                data.message ||
                (typeof detail === 'object' ? detail?.message : detail) ||
                'Job pending_dispatch — dispatcher will enqueue when Redis recovers',
              contentAndType: 'job_pending_dispatch-logs',
            } as Data,
          ]);
        }
        startPolling(id);
      } catch (err: any) {
        console.error('Failed to start research job:', err);
        setOrderedData((prev) => [
          ...prev,
          {
            type: 'logs',
            content: 'error',
            output: `Error: ${err?.message || err}`,
            contentAndType: 'error-logs',
          } as Data,
        ]);
        setLoading(false);
      }
    },
    [onlySessionId, setLoading, setAnswer, setOrderedData, startPolling, stopPolling]
  );

  const cancelResearchJob = useCallback(async () => {
    const id = jobId || loadStoredJob(onlySessionId)?.jobId;
    if (id) {
      try {
        await apiFetch(`/api/jobs/${id}/cancel`, { method: 'POST' });
        setOrderedData((prev) => [
          ...prev,
          {
            type: 'logs',
            content: 'job_cancelling',
            output: '已请求取消，等待 Worker 停止…',
            contentAndType: 'job_cancelling-logs',
          } as Data,
        ]);
        // Keep polling until cancelled/failed — do not fake immediate cancelled
        startPolling(id);
      } catch (err) {
        console.error('Cancel job failed:', err);
        setLoading(false);
      }
    } else {
      clearActiveJob();
      setLoading(false);
    }
  }, [jobId, onlySessionId, clearActiveJob, setLoading, setOrderedData, startPolling]);

  // Legacy alias — page.tsx still calls initializeWebSocket(...)
  const initializeWebSocket = startResearchJob;

  // Keep setSocket for HumanFeedback compatibility (unused in poll path)
  void setShowHumanFeedback;
  void setQuestionForHuman;

  return {
    socket,
    setSocket,
    jobId,
    startResearchJob,
    initializeWebSocket,
    observeJob,
    cancelResearchJob,
    resumeStoredJob,
    clearActiveJob,
  };
};
