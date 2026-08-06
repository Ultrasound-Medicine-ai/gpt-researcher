import { Data } from '../types/data';

const MAX_CONTEXT_LENGTH = 12000;

export function buildResearchContext(orderedData: Data[]): string {
  const sections: string[] = [];

  const subqueries = orderedData
    .filter((item) => (item as { content?: string }).content === 'subqueries')
    .flatMap((item) => {
      const meta = (item as { metadata?: unknown }).metadata;
      if (Array.isArray(meta)) return meta.map(String);
      if (meta != null) return [String(meta)];
      return [];
    });

  if (subqueries.length) {
    sections.push(
      `Research sub-queries:\n${subqueries.map((q) => `- ${q}`).join('\n')}`
    );
  }

  const urls = new Set<string>();
  orderedData.forEach((item) => {
    const record = item as { content?: string; metadata?: unknown; type?: string; items?: { url?: string }[] };
    if (record.content === 'added_source_url' && record.metadata) {
      urls.add(String(record.metadata));
    }
    if (record.type === 'sourceBlock' && record.items) {
      record.items.forEach((source) => {
        if (source.url) urls.add(source.url);
      });
    }
  });

  if (urls.size) {
    sections.push(
      `Sources consulted during research:\n${[...urls].map((url) => `- ${url}`).join('\n')}`
    );
  }

  const searchSnippets: string[] = [];
  orderedData.forEach((item) => {
    if (item.type !== 'chat') return;
    const toolCalls = (item as { metadata?: { tool_calls?: Array<{ tool?: string; search_metadata?: { sources?: Array<{ title?: string; url?: string; content?: string }> } }> } }).metadata?.tool_calls;
    toolCalls?.forEach((tool) => {
      if (tool.tool !== 'quick_search') return;
      tool.search_metadata?.sources?.forEach((source) => {
        searchSnippets.push(
          `- ${source.title || 'Source'} (${source.url || 'n/a'}): ${source.content || ''}`
        );
      });
    });
  });

  if (searchSnippets.length) {
    sections.push(`Web search results from prior chat:\n${searchSnippets.join('\n')}`);
  }

  const logSnippets: string[] = [];
  orderedData.forEach((item) => {
    const record = item as {
      type?: string;
      content?: string;
      output?: unknown;
      items?: Array<{ output?: unknown }>;
    };

    if (record.type === 'logs' && typeof record.output === 'string') {
      if (record.content && !['added_source_url', 'subqueries'].includes(record.content)) {
        const trimmed = record.output.trim();
        if (trimmed.length > 20 && trimmed.length < 2000) {
          logSnippets.push(trimmed);
        }
      }
    }

    if (record.type === 'accordionBlock' && record.items) {
      record.items.forEach((subItem) => {
        if (typeof subItem.output === 'string' && subItem.output.length > 20) {
          logSnippets.push(subItem.output.trim().slice(0, 500));
        }
      });
    }
  });

  if (logSnippets.length) {
    sections.push(`Research progress notes:\n${logSnippets.slice(-10).join('\n\n')}`);
  }

  let result = sections.join('\n\n');
  if (result.length > MAX_CONTEXT_LENGTH) {
    result = `${result.slice(0, MAX_CONTEXT_LENGTH)}\n...(truncated)`;
  }

  return result;
}
